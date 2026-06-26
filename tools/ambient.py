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
_AMBIENT_PATH = _ROOT / "data" / "ambient_context.json"
_PROFILE_PATH = _ROOT / "config" / "profile.yaml"

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
    if _PROFILE_PATH.exists():
        try:
            return yaml.safe_load(_PROFILE_PATH.read_text()) or {}
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

    _AMBIENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_AMBIENT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    parts = []
    if data["weather"]:
        parts.append(f"weather OK ({city})")
    else:
        parts.append("weather unavailable" + (
            f" (city: {city})" if city else " — set location.city in config/profile.yaml"
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
    time_label = now.strftime("%-I:%M %p")
    tz_label = f" ({tz_str})" if tz_str else ""
    lines = [
        "## Current Context",
        f"Date/time: {dt_label}, {time_label}{tz_label}",
    ]

    if not _AMBIENT_PATH.exists():
        return "\n".join(lines)

    try:
        data = json.loads(_AMBIENT_PATH.read_text())
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
