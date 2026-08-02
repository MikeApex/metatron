"""
core/spend_guard.py — in-process runaway protection.

GCP's budget data lags by hours, so the $70 soft cap and $150 hard cap cannot
react at runaway speed: a retry loop can burn a month's budget before a budget
alert fires. This layer sees every API call as it happens and reacts in seconds.

Two independent guards, because they fail differently:

  Rate limit   Counts pipeline sessions in a rolling hour. Needs no pricing data,
               so it keeps working if the rate table goes stale or a new cost
               source appears. This is the robust guard.
  Spend limit  Token counts x configured rates. Maps to real money so thresholds
               are meaningful, but depends on the table being roughly current.

Either can trip. Both warn before they stop, so the system does not go silent
without notice.

Deliberately fail-open on internal errors: a bug in cost accounting must never
take down a working assistant. The guard exists to catch runaway, not to become
a new source of outage. A hard stop only happens on a real threshold breach.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from datetime import date, datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _ROOT / "config" / "modules" / "spend_guard.yaml"
_STATE_DIR = _ROOT / "data" / "diagnostics"

_lock = threading.Lock()
_config: dict | None = None
_session_times: deque[datetime] = deque()
_alerted_spend = False
_alerted_rate = False


class SpendLimitExceeded(RuntimeError):
    """A daily spend or session-rate threshold was exceeded."""


def _load_config() -> dict:
    global _config
    if _config is None:
        try:
            _config = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        except Exception as exc:
            logger.warning(f"[spend_guard] config unreadable ({exc}) — guard disabled")
            _config = {"enabled": False}
    return _config


def _state_path(day: date | None = None) -> Path:
    return _STATE_DIR / f"spend_{(day or date.today()).isoformat()}.json"


def _read_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {"date": date.today().isoformat(), "usd": 0.0, "calls": 0, "tokens_in": 0, "tokens_out": 0}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"date": date.today().isoformat(), "usd": 0.0, "calls": 0, "tokens_in": 0, "tokens_out": 0}


def _write_state(state: dict) -> None:
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _state_path().write_text(json.dumps(state, indent=2))
    except Exception as exc:
        logger.warning(f"[spend_guard] could not persist state: {exc}")


def _rate_for(model: str) -> tuple[float, float]:
    pricing = _load_config().get("pricing", {}) or {}
    entry = pricing.get(model) or pricing.get("default") or {}
    return float(entry.get("input", 0.0)), float(entry.get("output", 0.0))


def estimate_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    in_rate, out_rate = _rate_for(model)
    return (tokens_in / 1_000_000.0) * in_rate + (tokens_out / 1_000_000.0) * out_rate


def record_tokens(model: str, tokens_in: int, tokens_out: int) -> None:
    """
    Add one API call to today's running total. Never raises.

    Called from the single place every provider path already reports token
    counts, so no provider needs to know this module exists.
    """
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return
    if not tokens_in and not tokens_out:
        return

    try:
        cost = estimate_usd(model or "default", tokens_in or 0, tokens_out or 0)
        with _lock:
            state = _read_state()
            if state.get("date") != date.today().isoformat():
                state = {"date": date.today().isoformat(), "usd": 0.0,
                         "calls": 0, "tokens_in": 0, "tokens_out": 0}
                globals()["_alerted_spend"] = False
            state["usd"] = round(state.get("usd", 0.0) + cost, 6)
            state["calls"] = state.get("calls", 0) + 1
            state["tokens_in"] = state.get("tokens_in", 0) + (tokens_in or 0)
            state["tokens_out"] = state.get("tokens_out", 0) + (tokens_out or 0)
            _write_state(state)
            _maybe_alert_spend(state, cfg)
    except Exception as exc:
        # Accounting must never break a working session.
        logger.warning(f"[spend_guard] record failed: {exc}")


def _maybe_alert_spend(state: dict, cfg: dict) -> None:
    global _alerted_spend
    alert_at = float(cfg.get("alert_usd_per_day", 0) or 0)
    if alert_at and state["usd"] >= alert_at and not _alerted_spend:
        _alerted_spend = True
        logger.warning(
            f"[spend_guard] ALERT estimated spend today ${state['usd']:.2f} "
            f"crossed ${alert_at:.2f} over {state['calls']} calls"
        )
        print(f"[spend_guard] ALERT ${state['usd']:.2f} today ({state['calls']} calls)", flush=True)


def note_session_start() -> None:
    """Record that a pipeline session began, for the rolling rate window."""
    with _lock:
        now = datetime.now()
        _session_times.append(now)
        cutoff = now.timestamp() - 3600
        while _session_times and _session_times[0].timestamp() < cutoff:
            _session_times.popleft()


def _sessions_last_hour() -> int:
    now = datetime.now().timestamp()
    return sum(1 for t in _session_times if t.timestamp() >= now - 3600)


def check_before_session() -> None:
    """
    Raise SpendLimitExceeded if today's spend or the hourly session rate has
    passed its stop threshold. Call before starting a pipeline session.
    """
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return

    global _alerted_rate
    try:
        stop_usd = float(cfg.get("stop_usd_per_day", 0) or 0)
        stop_rate = int(cfg.get("stop_sessions_per_hour", 0) or 0)
        alert_rate = int(cfg.get("alert_sessions_per_hour", 0) or 0)

        recent = _sessions_last_hour()
        if alert_rate and recent >= alert_rate and not _alerted_rate:
            _alerted_rate = True
            logger.warning(f"[spend_guard] ALERT {recent} sessions in the last hour")
            print(f"[spend_guard] ALERT {recent} sessions in the last hour", flush=True)

        if stop_rate and recent >= stop_rate:
            raise SpendLimitExceeded(
                f"{recent} sessions started in the last hour, at or above the limit of "
                f"{stop_rate}. Something is looping. Sessions are paused; edit "
                f"config/modules/spend_guard.yaml or restart the server to clear."
            )

        spend = _read_state().get("usd", 0.0)
        if stop_usd and spend >= stop_usd:
            raise SpendLimitExceeded(
                f"Estimated AI spend today is ${spend:.2f}, at or above the daily limit of "
                f"${stop_usd:.2f}. Sessions are paused until tomorrow, or until "
                f"config/modules/spend_guard.yaml is changed."
            )
    except SpendLimitExceeded:
        raise
    except Exception as exc:
        # Fail open: a bug here must not take down a working assistant.
        logger.warning(f"[spend_guard] check failed, allowing session: {exc}")


def today_summary() -> dict:
    """Current totals, for diagnostics and the monitor."""
    state = _read_state()
    state["sessions_last_hour"] = _sessions_last_hour()
    return state
