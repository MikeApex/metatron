"""
tools/ambient.py — ambient world context fetcher.

Fetches weather (wttr.in), top headlines (BBC + CNN RSS), and optionally
major market indices (Yahoo Finance). Writes to data/ambient_context.json.
Runs every 3 hours via the scheduler.

Cloud-safe: only the home city name is sent to wttr.in — no personal data.
Date/time is always read from the system clock at load time so it is always
current regardless of when the file was last refreshed.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests
import yaml

_ROOT = Path(__file__).parent.parent
from core.persona import persona_config_dir, persona_data_dir


def _ambient_path() -> Path:
    return persona_data_dir() / "ambient_context.json"


def _profile_path() -> Path:
    return persona_config_dir() / "profile.yaml"

_MARKET_SYMBOLS = ["^GSPC", "^FTSE", "^GDAXI", "^N225", "^HSI", "GC=F", "CL=F"]
_MARKET_NAMES = {
    "^GSPC": "S&P 500",
    "^FTSE": "FTSE 100",
    "^GDAXI": "DAX",
    "^N225": "Nikkei",
    "^HSI": "Hang Seng",
    "GC=F": "Gold",
    "CL=F": "WTI Oil",
}


def _read_profile() -> dict:
    path = _profile_path()
    if path.exists():
        try:
            return yaml.safe_load(path.read_text()) or {}
        except Exception:
            pass
    return {}


def _get_timezone() -> str | None:
    return _read_profile().get("location", {}).get("timezone")


def _get_home_city() -> str | None:
    return _read_profile().get("location", {}).get("city")


def _markets_enabled() -> bool:
    return bool(_read_profile().get("ambient", {}).get("markets", False))


def _now_local() -> datetime:
    tz_str = _get_timezone()
    if tz_str:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz_str))
        except Exception:
            pass
    return datetime.now()


def format_receipt_time(dt: datetime) -> str:
    """
    Format a UTC-aware timestamp (e.g. message receipt time, captured in
    core/server.py) in the persona's local timezone, seconds precision.
    Mirrors the date/time formatting in load_ambient_context() so the two
    read the same to the agent.
    """
    tz_str = _get_timezone()
    if tz_str:
        try:
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo(tz_str))
        except Exception:
            pass
    dt_label = dt.strftime("%A, %B %-d, %Y")
    time_label = dt.strftime("%-I:%M:%S %p")
    tz_label = f" ({tz_str})" if tz_str else ""
    return f"{dt_label}, {time_label}{tz_label}"


def current_clock_line() -> str:
    """
    One-line authoritative system clock, worded to match load_ambient_context().

    For agents that receive no ambient block. Specialists are given only the
    Coordinator's directive, which carries no date — so a specialist writing a
    dated record has nothing to anchor to and will invent a date.
    """
    return (
        "System clock (authoritative — trust this over any date or time stated "
        f"in your directive): {format_receipt_time(_now_local())}"
    )


def _fetch_weather(city: str) -> dict | None:
    try:
        response = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
        response.raise_for_status()
        data = response.json()
        c = data["current_condition"][0]
        return {
            "temp_c": c["temp_C"],
            "feels_like_c": c["FeelsLikeC"],
            "description": c["weatherDesc"][0]["value"],
            "humidity_pct": c["humidity"],
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Agent-callable weather tools
#
# Distinct from the ambient block above, which is a passive 3-hourly refresh
# written into every head-layer prompt. These are pulled deliberately by the
# Research Agent when a decision actually turns on the weather, and passed up
# to the Synthesizer to colour what it recommends.
#
# Cloud-safe: only a city name leaves the machine.
# ---------------------------------------------------------------------------

_UV_BANDS = [(3, "low"), (6, "moderate"), (8, "high"), (11, "very high")]
_AQI_BANDS = [(20, "good"), (40, "fair"), (60, "moderate"), (80, "poor"), (100, "very poor")]


def _band(value: float | None, bands: list[tuple[int, str]], top: str) -> str:
    """Map a numeric index onto its published category label."""
    if value is None:
        return "unknown"
    for threshold, label in bands:
        if value < threshold:
            return label
    return top


def _wttr(city: str) -> dict:
    """Raw wttr.in j1 payload. Raises on failure — callers decide how to degrade."""
    r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=15)
    r.raise_for_status()
    return r.json()


def _coords(payload: dict) -> tuple[float, float] | None:
    """
    Pull lat/lon out of the wttr.in response.

    wttr.in already resolves the city, so reusing its coordinates avoids a
    separate geocoding call and keeps the two sources talking about the
    same place.
    """
    try:
        area = payload["nearest_area"][0]
        return float(area["latitude"]), float(area["longitude"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _recent_rain(lat: float, lon: float, past_days: int = 7) -> dict | None:
    """
    Daily rainfall totals for the past week, plus days since it last rained.

    wttr.in only looks forward, but the decisions that turn on rain are
    backward-looking — whether the garden needs watering depends on what has
    already fallen. Open-Meteo is free and needs no API key.
    """
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "precipitation_sum",
                "past_days": past_days, "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=15,
        )
        r.raise_for_status()
        daily = r.json().get("daily", {})
        dates = daily.get("time", []) or []
        sums = daily.get("precipitation_sum", []) or []

        history = [
            {"date": d, "precip_mm": p}
            for d, p in zip(dates, sums)
            if p is not None
        ]
        # Count back from the most recent day. "Rain" means a measurable
        # amount — a trace of 0.05mm does not water a garden.
        days_since = None
        for i, entry in enumerate(reversed(history)):
            if entry["precip_mm"] >= 1.0:
                days_since = i
                break

        total = round(sum(e["precip_mm"] for e in history), 1)
        window = len(history)
        # A bare null for days_since_rain reads identically to "lookup failed",
        # and a model acting on that ambiguity gets the decision backwards. Say
        # which it is in words.
        if days_since is None:
            summary = (
                f"No measurable rain (>=1mm) in the last {window} days; "
                f"{total}mm total."
            )
        elif days_since == 0:
            summary = f"Rained today. {total}mm over the last {window} days."
        else:
            summary = (
                f"Last measurable rain was {days_since} day(s) ago; "
                f"{total}mm over the last {window} days."
            )

        return {
            "daily_history": history,
            "days_since_rain": days_since,
            "rained_in_window": days_since is not None,
            "window_days": window,
            "total_mm_last_7_days": total,
            "summary": summary,
        }
    except Exception:
        return None


def _air_quality(lat: float, lon: float) -> dict | None:
    """Current air quality from Open-Meteo. Free, no API key. None on failure."""
    try:
        r = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude": lat, "longitude": lon,
                "current": "european_aqi,us_aqi,pm2_5,pm10",
                "timezone": "auto",
            },
            timeout=15,
        )
        r.raise_for_status()
        cur = r.json().get("current", {})
        eu = cur.get("european_aqi")
        return {
            "european_aqi": eu,
            "us_aqi": cur.get("us_aqi"),
            "pm2_5": cur.get("pm2_5"),
            "pm10": cur.get("pm10"),
            "category": _band(eu, _AQI_BANDS, "extremely poor"),
        }
    except Exception:
        return None


def _current_block(payload: dict) -> dict:
    c = payload["current_condition"][0]
    uv = int(c.get("uvIndex") or 0)
    return {
        "temp_c": c["temp_C"],
        "feels_like_c": c["FeelsLikeC"],
        "description": c["weatherDesc"][0]["value"],
        "humidity_pct": c["humidity"],
        "cloudcover_pct": c.get("cloudcover"),
        "wind_kmph": c.get("windspeedKmph"),
        "precip_mm_now": c.get("precipMM"),
        "uv_index": uv,
        "uv_category": _band(uv, _UV_BANDS, "extreme"),
    }


def get_weather(location: str = "", days: int = 3) -> dict:
    """
    Current conditions, a short forecast, and recent rainfall for a location.

    Recent rainfall is the part most decisions actually hinge on — whether the
    garden needs watering, whether a run is realistic — so `days_since_rain`
    is computed rather than left for the caller to derive.

    Args:
        location: City name. Defaults to the persona's home city.
        days:     Forecast days to include (1-3).

    Returns:
        Dict with current, forecast, recent_rain — or {"error": ...}.
    """
    city = (location or "").strip() or _get_home_city()
    if not city:
        return {"error": "No location given and no home city set in profile.yaml."}

    try:
        payload = _wttr(city)
    except Exception as e:
        return {"error": f"Weather lookup failed for '{city}': {e}"}

    try:
        days = max(1, min(int(days), 3))
    except (TypeError, ValueError):
        days = 3

    forecast = []
    for day in payload.get("weather", [])[:days]:
        hourly = day.get("hourly", []) or []
        forecast.append({
            "date": day.get("date"),
            "max_temp_c": day.get("maxtempC"),
            "min_temp_c": day.get("mintempC"),
            "uv_index": day.get("uvIndex"),
            "total_precip_mm": round(
                sum(float(h.get("precipMM") or 0) for h in hourly), 1
            ),
            "max_chance_of_rain_pct": max(
                (int(h.get("chanceofrain") or 0) for h in hourly), default=0
            ),
        })

    result = {
        "location": city,
        "current": _current_block(payload),
        "forecast": forecast,
    }

    coords = _coords(payload)
    if coords:
        rain = _recent_rain(*coords)
        if rain:
            result["recent_rain"] = rain
    return result


def get_environmental_snapshot(location: str = "", date: str = "") -> dict:
    """
    Weather, UV index and air quality for a location.

    Feeds Physical Health's outdoor-activity and vitamin-D reasoning via the
    Research Agent. Fails soft: air quality comes from a second provider, and
    losing it must never take down a health session, so the snapshot returns
    without it rather than erroring.

    Args:
        location: City name. Defaults to the persona's home city.
        date:     Accepted for interface stability; only current conditions are
                  available from the free sources. Ignored.

    Returns:
        Dict with weather, uv, air_quality (possibly None) — or {"error": ...}.
    """
    city = (location or "").strip() or _get_home_city()
    if not city:
        return {"error": "No location given and no home city set in profile.yaml."}

    try:
        payload = _wttr(city)
    except Exception as e:
        return {"error": f"Environmental lookup failed for '{city}': {e}"}

    current = _current_block(payload)
    snapshot = {
        "location": city,
        "observed_at": payload["current_condition"][0].get("observation_time"),
        "weather": {k: v for k, v in current.items() if not k.startswith("uv_")},
        "uv": {
            "index": current["uv_index"],
            "category": current["uv_category"],
            # Vitamin D synthesis needs UV >= 3; below that, exposure time is
            # irrelevant regardless of how long someone is outside.
            "vitamin_d_synthesis_possible": current["uv_index"] >= 3,
        },
        "air_quality": None,
    }

    coords = _coords(payload)
    if coords:
        aq = _air_quality(*coords)
        if aq:
            snapshot["air_quality"] = aq
    if snapshot["air_quality"] is None:
        snapshot["air_quality_note"] = (
            "Air quality unavailable from the secondary source; "
            "weather and UV are unaffected."
        )
    return snapshot


GET_WEATHER_SCHEMA = {
    "name": "get_weather",
    "description": (
        "Current weather, a short forecast, and recent rainfall for a location. "
        "Use when a decision actually depends on the weather — whether outdoor "
        "activity is realistic, whether the garden needs watering, whether travel "
        "needs rethinking. Includes 'days_since_rain' and 7-day rainfall totals, "
        "so questions like 'has it rained lately?' can be answered directly. "
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
                "description": "Forecast days to include, 1-3. Defaults to 3.",
            },
        },
        "required": [],
    },
}

GET_ENVIRONMENTAL_SNAPSHOT_SCHEMA = {
    "name": "get_environmental_snapshot",
    "description": (
        "Weather, UV index and air quality for a location. Use for health-related "
        "outdoor decisions: whether air quality supports exercise outside, whether "
        "UV is high enough for vitamin D synthesis (index 3+) or high enough to "
        "warrant sun protection. Air quality comes from a secondary source and may "
        "be null; weather and UV are still returned when it is. "
        "Defaults to the user's home city if no location is given."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name (e.g. 'London'). Omit for the user's home city.",
            },
            "date": {
                "type": "string",
                "description": "Reserved; only current conditions are available. Ignored.",
            },
        },
        "required": [],
    },
}


def _fetch_rss_headlines(url: str, n: int) -> list[str]:
    try:
        import xml.etree.ElementTree as ET
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
        return [
            item.findtext("title", "").strip()
            for item in root.findall(".//item")[:n]
            if item.findtext("title", "").strip()
        ]
    except Exception:
        return []


def _fetch_headlines(n_each: int = 4) -> list[str] | None:
    """Fetch headlines from BBC and CNN, interleaved."""
    bbc = _fetch_rss_headlines("https://feeds.bbci.co.uk/news/rss.xml", n=n_each)
    cnn = _fetch_rss_headlines("http://rss.cnn.com/rss/edition.rss", n=n_each)

    # Interleave: BBC, CNN, BBC, CNN …
    interleaved = []
    for pair in zip(bbc, cnn):
        interleaved.extend(pair)
    # Append any extras from the longer list
    for item in bbc[len(cnn):]:
        interleaved.append(item)
    for item in cnn[len(bbc):]:
        interleaved.append(item)

    return interleaved or None


def _fetch_one_market(symbol: str) -> dict | None:
    """Fetch a single market symbol from Yahoo Finance v8 chart endpoint."""
    encoded = symbol.replace("^", "%5E")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?interval=1d&range=2d"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        meta = response.json()["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose")
        if price is None:
            return None
        change_pct = ((price - prev) / prev * 100) if prev else None
        return {
            "symbol": symbol,
            "name": _MARKET_NAMES.get(symbol, symbol),
            "price": round(price, 2),
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
        }
    except Exception:
        return None


def _fetch_markets() -> list[dict] | None:
    """Fetch major global market indices from Yahoo Finance."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    markets = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_fetch_one_market, sym): sym for sym in _MARKET_SYMBOLS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                markets.append(result)
    # Restore original symbol order for consistent output
    order = {sym: i for i, sym in enumerate(_MARKET_SYMBOLS)}
    markets.sort(key=lambda m: order.get(m["symbol"], 99))
    return markets or None


def refresh_ambient_context() -> str:
    """
    Fetch weather, news, and (if enabled) markets. Writes to data/ambient_context.json.
    Called by the scheduler every 3 hours. Returns a status string.
    """
    city = _get_home_city()
    now = _now_local()

    data: dict = {
        "fetched_at": now.isoformat(),
        "weather": _fetch_weather(city) if city else None,
        "news_headlines": _fetch_headlines(n_each=4),
        "markets": _fetch_markets() if _markets_enabled() else None,
    }

    ambient_path = _ambient_path()
    ambient_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ambient_path, "w") as f:
        json.dump(data, f, indent=2)

    parts = []
    if data["weather"]:
        parts.append(f"weather OK ({city})")
    else:
        parts.append("weather unavailable" + (
            f" (city: {city})" if city else " — set location.city in config/personas/{persona}/profile.yaml"
        ))
    headlines = data.get("news_headlines") or []
    parts.append(f"{len(headlines)} headlines" if headlines else "news unavailable")
    if data.get("markets"):
        parts.append(f"{len(data['markets'])} market indices")

    return f"Ambient context refreshed: {', '.join(parts)}"


def load_ambient_context() -> str:
    """
    Format ambient context as a system-prompt section.
    Date/time is always live from the system clock.
    Weather, news, and markets come from the last refresh (up to 3 hours old).
    """
    now = _now_local()
    tz_str = _get_timezone()

    dt_label = now.strftime("%A, %B %-d, %Y")
    time_label = now.strftime("%-I:%M:%S %p")
    tz_label = f" ({tz_str})" if tz_str else ""
    lines = [
        "## Current Context",
        f"System clock (authoritative — trust this over any time the user states in their message): {dt_label}, {time_label}{tz_label}",
    ]

    ambient_path = _ambient_path()
    if not ambient_path.exists():
        return "\n".join(lines)

    try:
        data = json.loads(ambient_path.read_text())
    except Exception:
        return "\n".join(lines)

    w = data.get("weather")
    if w:
        desc = w.get("description", "")
        temp = w.get("temp_c", "?")
        feels = w.get("feels_like_c", "?")
        humidity = w.get("humidity_pct", "?")
        lines.append(f"Weather: {desc}, {temp}°C (feels like {feels}°C), humidity {humidity}%")

    headlines = data.get("news_headlines")
    if headlines:
        lines.append("Headlines: " + " | ".join(headlines))

    markets = data.get("markets")
    if markets:
        parts = []
        for m in markets:
            name = m["name"]
            price = m["price"]
            chg = m.get("change_pct")
            sign = "+" if chg and chg > 0 else ""
            chg_str = f" ({sign}{chg:.1f}%)" if chg is not None else ""
            parts.append(f"{name} {price:,.0f}{chg_str}")
        lines.append("Markets: " + " | ".join(parts))

    return "\n".join(lines)
