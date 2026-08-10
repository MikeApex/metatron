"""
tools/flights.py — flight status via AeroDataBox (RapidAPI).

Built for the pre-departure travel check, same purpose as tools/tfl_status.py: know before
the user asks whether a flight is on time. `fetch_url` can't answer this — Heathrow's and
BA's own status pages are client-rendered SPAs that return an empty app shell to a plain
GET, confirmed by testing directly (see archive/plans/level3_web_actions_scope_2026-08-06.md).

Requires AERODATABOX_API_KEY in .env — AeroDataBox via RapidAPI's Basic plan (free,
unrestricted duration; 600 units/month, 1 req/s rate limit). Verified against
AeroDataBox's own pricing page, not an aggregator summary — API.Market's Basic plan is a
7-day trial; RapidAPI's is the genuinely ongoing free one. The 1 req/s limit is real
(hit it live while testing) and matches this tool's actual call pattern: a handful of
checks on travel days, not a polling loop.
"""

from __future__ import annotations

import os
from datetime import datetime

import requests

TIMEOUT_SECONDS = 10
_HOST = "aerodatabox.p.rapidapi.com"
_BASE = f"https://{_HOST}"


def _api_key() -> str | None:
    return os.environ.get("AERODATABOX_API_KEY")


def get_flight_status(flight_number: str, date: str = "") -> dict:
    """
    Current status of a scheduled flight by flight number.

    Args:
        flight_number: IATA flight number, e.g. "BA117" (airline code + number, no space
            required — the API accepts both).
        date: Optional "YYYY-MM-DD". Omit for the next/current scheduled occurrence.

    Returns:
        {"flights": [{"number", "airline", "status", "departure": {...}, "arrival": {...}}]}
        or {"error": ...}. An empty "flights" list means no matching flight was found —
        say so plainly rather than guessing; do not invent a status.
    """
    key = _api_key()
    if not key:
        return {"error": "Flight status is not configured (AERODATABOX_API_KEY missing)."}

    num = (flight_number or "").strip().replace(" ", "")
    if not num:
        return {"error": "No flight number given."}

    path = f"/flights/number/{num}"
    if date:
        path += f"/{date.strip()}"

    try:
        resp = requests.get(
            f"{_BASE}{path}",
            headers={"x-rapidapi-host": _HOST, "x-rapidapi-key": key},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        return {"error": f"Flight status lookup failed: {e}"}

    if resp.status_code == 204:
        return {"flights": []}
    if resp.status_code == 429:
        return {"error": "Flight status rate limit hit (1 request/second on this plan) — try again shortly."}
    if not resp.ok:
        return {"error": f"Flight status lookup failed: HTTP {resp.status_code}."}

    try:
        data = resp.json()
    except ValueError:
        return {"error": "Flight status returned an unparseable response."}

    def _leg(point: dict) -> dict:
        airport = point.get("airport") or {}
        sched = (point.get("scheduledTime") or {}).get("local", "")
        # Airlines report a delay under different fields depending on flight phase —
        # "revisedTime" once a new estimate exists, "predictedTime" for a forecast ahead
        # of departure, "runwayTime" for the actual wheels-up/down moment.
        actual = (
            (point.get("runwayTime") or {}).get("local")
            or (point.get("revisedTime") or {}).get("local")
            or (point.get("predictedTime") or {}).get("local")
            or ""
        )
        # "delayed" means *later than* scheduled, not merely *different from* it. Comparing
        # the two strings flagged BA464's arrival as delayed on an estimate 28 minutes
        # EARLY (2026-08-10). Logistics only speaks up when a flight is off schedule, so
        # that turned every early arrival into a delay warning. An unparseable stamp falls
        # back to not-delayed: a missed delay is quieter than an invented one.
        delta_minutes = 0
        if actual and actual != sched:
            try:
                delta_minutes = round(
                    (datetime.fromisoformat(actual) - datetime.fromisoformat(sched)).total_seconds() / 60
                )
            except ValueError:
                delta_minutes = 0
        return {
            "airport": airport.get("name", "?"),
            "iata": airport.get("iata", "?"),
            "terminal": point.get("terminal", ""),
            "scheduled_local": sched,
            "current_estimate_local": actual or sched,
            # Negative = running early. Both are worth knowing; only positive is a delay.
            "delay_minutes": delta_minutes,
            "delayed": delta_minutes > 0,
        }

    flights = []
    for f in data if isinstance(data, list) else []:
        flights.append({
            "number": f.get("number", num),
            "airline": (f.get("airline") or {}).get("name", "?"),
            "status": f.get("status", "Unknown"),
            "departure": _leg(f.get("departure") or {}),
            "arrival": _leg(f.get("arrival") or {}),
        })

    return {"flights": flights}


GET_FLIGHT_STATUS_SCHEMA = {
    "name": "get_flight_status",
    "description": (
        "Current status of a scheduled flight by flight number (e.g. 'BA117') — on time, "
        "delayed, cancelled, arrived, with departure/arrival airport, terminal, and "
        "scheduled vs. current-estimate times. Use ahead of a travel day to check before "
        "the user asks. Rate-limited to 1 request/second on the current plan — call once "
        "per flight, not in a tight loop. An empty result means no matching flight was "
        "found; say so rather than guessing at a status."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "flight_number": {
                "type": "string",
                "description": "IATA flight number, e.g. 'BA117'.",
            },
            "date": {
                "type": "string",
                "description": "Optional 'YYYY-MM-DD'. Omit for the next/current scheduled occurrence.",
            },
        },
        "required": ["flight_number"],
    },
}
