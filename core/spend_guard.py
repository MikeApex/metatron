"""
core/spend_guard.py — in-process runaway protection.

GCP's budget data lags by hours, so neither the soft cap (stops the VM) nor the
hard cap (disables billing) can react at runaway speed: a retry loop can burn a
month's budget before a budget alert fires. This layer sees every API call as it
happens and reacts in seconds.

The cap amounts are deliberately not written here — docs/INFRASTRUCTURE.md
§ Billing protection is the source of truth. This docstring said $70/$150 through
two raises and a revert; nothing in this module reads those numbers.

Two independent guards, because they fail differently:

  Rate limit   Counts pipeline sessions in a rolling hour. Needs no pricing data,
               so it keeps working if the rate table goes stale or a new cost
               source appears. This is the robust guard.
  Spend limit  Token counts x configured rates. Maps to real money so thresholds
               are meaningful, but depends on the table being roughly current.

A per-call meter cannot see a cost billed by the clock, and on 2026-08-19 that
gap read $2.63 against a $6.12 bill: Vertex context-cache STORAGE bills per
wall-clock hour whether or not anything reads the cache. record_cache_storage()
closes it. The lesson generalises past caching — anything this system creates
that outlives the call that created it has to report itself here, or the guard's
silence will be read as safety.

Both thresholds judge usd_billed_est, not usd. The guard sees pipeline turns and
nothing else, while Vertex also bills cache creation and retried attempts — ~18%
of invocations but only ~12% of tokens, measured over ten days to 2026-08-28.
`usd` stays the raw observed sum so it can be checked against the pricing table;
the uplift that closes the gap is applied at the point of judgement. Take the
figure from config/modules/spend_guard.yaml, unmetered_uplift, and re-derive it
by that key's instructions — the count is only meaningful once every state file
is summed, which is what _budget_root() below exists to guarantee.

Either can trip. Both warn before they stop, so the system does not go silent
without notice.

Deliberately fail-open on internal errors: a bug in cost accounting must never
take down a working assistant. The guard exists to catch runaway, not to become
a new source of outage. A hard stop only happens on a real threshold breach.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
from collections import deque
from datetime import date, datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _ROOT / "config" / "modules" / "spend_guard.yaml"


def _budget_root() -> Path:
    """
    The directory whose data/diagnostics holds this HOST's single daily budget.

    Normally _ROOT. In a git worktree it is the MAIN working tree instead, because
    a worktree is a second checkout of the same repo on the same machine billing
    the same Vertex project — but _ROOT resolves from __file__, so each worktree
    got its own state file and therefore its own full daily budget.

    Measured, not theoretical: on 2026-08-28 the coordinator model probe ran in
    .claude/worktrees/agent-a53d4604ec183981e and wrote $1.94 / 196 calls /
    169,609 output tokens into a state file the main checkout has never read. The
    day's real spend was ~3x the config threshold's worth of independent budgets
    while every state file individually read as quiet. That is the exact failure
    the module header describes for two HOSTS, reproduced within one host — and
    it is worse, because the header's mitigation (thresholds set with two hosts in
    mind) cannot be sized against a worktree count that changes per session.

    Not solved by a shared counter across hosts, for the reason the header gives:
    the hosts share no filesystem. Worktrees DO share one, so here the fix is free
    — no network, no lock beyond the one already held, no new failure mode.

    Fails open to _ROOT on anything unexpected. A guard that cannot find the main
    checkout must still count, in the wrong place, rather than not count at all.
    """
    try:
        git = _ROOT / ".git"
        # A worktree's .git is a FILE holding "gitdir: <main>/.git/worktrees/<name>".
        # A normal checkout's .git is a directory — the VM, and the main Mac tree.
        if not git.is_file():
            return _ROOT
        line = git.read_text(encoding="utf-8", errors="replace").strip()
        if not line.startswith("gitdir:"):
            return _ROOT
        gitdir = Path(line.split(":", 1)[1].strip())
        if not gitdir.is_absolute():
            gitdir = (_ROOT / gitdir).resolve()
        # .../<main>/.git/worktrees/<name>  ->  .../<main>
        if gitdir.parent.name != "worktrees" or gitdir.parent.parent.name != ".git":
            return _ROOT
        main_root = gitdir.parent.parent.parent
        return main_root if main_root.is_dir() else _ROOT
    except Exception:
        return _ROOT


_STATE_DIR = _budget_root() / "data" / "diagnostics"

# The thresholds below are PER HOST, and more than one host bills the same
# Vertex project. The VM runs production; the Mac holds Vertex ADC and runs the
# A4/B1 suites against the same project — on 2026-08-08 it had spent $8.63 to the
# VM's $7.06, in a state file the VM has never seen. Two hosts therefore mean two
# independent daily budgets and an effective ceiling of 2x what the config reads.
#
# Not solved by a shared counter on purpose: the hosts share no filesystem, so
# sharing state would put a network round-trip in front of every session inside a
# guard whose first design rule is that it must never become a source of outage.
# The host is recorded instead, so the split is visible in the state file and in
# every alert, and the config thresholds are set with two hosts in mind.
_HOST = socket.gethostname()

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


def _blank_state() -> dict:
    return {"date": date.today().isoformat(), "host": _HOST,
            "usd": 0.0, "calls": 0, "tokens_in": 0, "tokens_out": 0,
            "tokens_cached": 0, "usd_cache_storage": 0.0, "cache_grants": 0,
            "usd_billed_est": 0.0}


def _read_state() -> dict:
    path = _state_path()
    if not path.exists():
        return _blank_state()
    try:
        state = json.loads(path.read_text())
        state.setdefault("host", _HOST)
        return state
    except Exception:
        return _blank_state()


def _write_state(state: dict) -> None:
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _state_path().write_text(json.dumps(state, indent=2))
    except Exception as exc:
        logger.warning(f"[spend_guard] could not persist state: {exc}")


def _normalise_model(model: str) -> str:
    """
    Strip the 'models/' prefix that AI Studio uses and Vertex does not.

    Traces record the prefixed form, so an unprefixed pricing table missed every
    lookup and silently fell through to the default rate — pricing all the cheap
    Flash-Lite traffic as if it were Pro, and overstating spend by roughly 8x.
    """
    name = (model or "").strip()
    if name.startswith("models/"):
        name = name[len("models/"):]
    return name


def _rate_for(model: str) -> tuple[float, float]:
    pricing = _load_config().get("pricing", {}) or {}
    name = _normalise_model(model)
    entry = pricing.get(name)
    if entry is None:
        # Prefix match, so a dated or -preview suffix still resolves.
        for key, val in pricing.items():
            if key != "default" and name.startswith(key):
                entry = val
                break
    if entry is None:
        entry = pricing.get("default") or {}
        if name:
            logger.warning(f"[spend_guard] no rate for model {name!r} — using default")
    return float(entry.get("input", 0.0)), float(entry.get("output", 0.0))


def _entry_for(model: str) -> dict:
    pricing = _load_config().get("pricing", {}) or {}
    name = _normalise_model(model)
    entry = pricing.get(name)
    if entry is None:
        for key, val in pricing.items():
            if key != "default" and name.startswith(key):
                entry = val
                break
    return entry or pricing.get("default") or {}


def estimate_usd(model: str, tokens_in: int, tokens_out: int,
                 tokens_cached: int = 0) -> float:
    """
    Cost of one call. `tokens_cached` is the part of `tokens_in` served from a
    Vertex context cache — INCLUDED in the provider's input count, never added to
    it, so it is subtracted out and re-priced at the cached rate rather than
    double-counted.
    """
    in_rate, out_rate = _rate_for(model)
    cached_rate = float(_entry_for(model).get("cached_input", in_rate))
    tokens_cached = max(0, min(tokens_cached or 0, tokens_in or 0))
    uncached = (tokens_in or 0) - tokens_cached
    return (uncached / 1_000_000.0) * in_rate \
        + (tokens_cached / 1_000_000.0) * cached_rate \
        + ((tokens_out or 0) / 1_000_000.0) * out_rate


def record_cache_storage(model: str, tokens: int, minutes: float) -> None:
    """
    Charge a context cache's storage for the window it has just been granted.

    CHARGED AT GRANT TIME, NOT AT DELETE, and the whole window at once. This
    module has no clock — it only runs when a call happens — so a delete-time
    charge would be skipped by exactly the event that makes storage expensive: a
    crash that orphans the cache. Charging the full window up front is a slight
    overestimate on a cache deleted early, never an underestimate, and it needs
    no timer to be correct.

    Call once when a cache is created and again on every expiry refresh, with
    the length of the window granted.
    """
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return
    if not tokens or minutes <= 0:
        return
    try:
        rate = float(_entry_for(model).get("cache_storage_per_hour", 0.0) or 0.0)
        if not rate:
            logger.warning(f"[spend_guard] no cache storage rate for {model!r} — storage not counted")
            return
        cost = (tokens / 1_000_000.0) * rate * (minutes / 60.0)
        with _lock:
            state = _read_state()
            if state.get("date") != date.today().isoformat():
                state = _blank_state()
                globals()["_alerted_spend"] = False
            state["usd"] = round(state.get("usd", 0.0) + cost, 6)
            state["usd_cache_storage"] = round(state.get("usd_cache_storage", 0.0) + cost, 6)
            state["cache_grants"] = state.get("cache_grants", 0) + 1
            _write_state(state)
            _maybe_alert_spend(state, cfg)
    except Exception as exc:
        logger.warning(f"[spend_guard] cache storage record failed: {exc}")


def record_tokens(model: str, tokens_in: int, tokens_out: int,
                  tokens_cached: int = 0) -> None:
    """
    Add one API call to today's running total. Never raises.

    Called from the single place every provider path already reports token
    counts, so no provider needs to know this module exists.

    tokens_cached is the cache-served share of tokens_in; providers that do not
    report one pass 0 and are priced exactly as before.
    """
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return
    if not tokens_in and not tokens_out:
        return

    try:
        cost = estimate_usd(model or "default", tokens_in or 0, tokens_out or 0, tokens_cached or 0)
        with _lock:
            state = _read_state()
            if state.get("date") != date.today().isoformat():
                state = _blank_state()
                globals()["_alerted_spend"] = False
            state["usd"] = round(state.get("usd", 0.0) + cost, 6)
            state["calls"] = state.get("calls", 0) + 1
            state["tokens_in"] = state.get("tokens_in", 0) + (tokens_in or 0)
            state["tokens_out"] = state.get("tokens_out", 0) + (tokens_out or 0)
            state["tokens_cached"] = state.get("tokens_cached", 0) + (tokens_cached or 0)
            _write_state(state)
            _maybe_alert_spend(state, cfg)
    except Exception as exc:
        # Accounting must never break a working session.
        logger.warning(f"[spend_guard] record failed: {exc}")


def _billed_estimate(state: dict, cfg: dict) -> float:
    """
    What the day is likely to actually BILL, as opposed to what was observed.

    `state["usd"]` is the honest sum of pipeline turns — the only thing this
    module is called for. Vertex bills more: context-cache creation ingests a
    whole prompt with no generate call attached, and retried or fallback attempts
    are billed but leave no trace record to count. Both are invisible here; over
    the ten days to 2026-08-28 they ran ~18% of invocations and ~12% of tokens,
    and it is the token share the uplift is sized to, because dollars follow
    tokens and a cache creation is one cheap-but-large "call".

    The raw figure stays raw so the arithmetic remains auditable against the
    pricing table; the uplift is applied only where a judgement is made — the
    alert, the stop, and the reported summary. Derivation and how to re-measure:
    config/modules/spend_guard.yaml, unmetered_uplift.
    """
    try:
        factor = float(cfg.get("unmetered_uplift", 1.0) or 1.0)
    except (TypeError, ValueError):
        factor = 1.0
    # Never scale DOWN: a factor below 1 would make the guard read under what it
    # actually observed, which no measurement could justify.
    return round(state.get("usd", 0.0) * max(1.0, factor), 6)


def _maybe_alert_spend(state: dict, cfg: dict) -> None:
    global _alerted_spend
    alert_at = float(cfg.get("alert_usd_per_day", 0) or 0)
    billed = _billed_estimate(state, cfg)
    state["usd_billed_est"] = billed
    if alert_at and billed >= alert_at and not _alerted_spend:
        _alerted_spend = True
        logger.warning(
            f"[spend_guard] ALERT estimated spend today ${billed:.2f} on {_HOST} "
            f"(${state['usd']:.2f} observed + unmetered uplift) "
            f"crossed ${alert_at:.2f} over {state['calls']} calls "
            f"(this host only — other hosts count separately)"
        )
        print(f"[spend_guard] ALERT ${billed:.2f} today on {_HOST} "
              f"({state['calls']} calls)", flush=True)


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

        spend = _billed_estimate(_read_state(), cfg)
        if stop_usd and spend >= stop_usd:
            raise SpendLimitExceeded(
                f"Estimated AI spend today on {_HOST} is ${spend:.2f}, at or above the "
                f"daily limit of ${stop_usd:.2f}. Sessions are paused until tomorrow, "
                f"or until config/modules/spend_guard.yaml is changed."
            )
    except SpendLimitExceeded:
        raise
    except Exception as exc:
        # Fail open: a bug here must not take down a working assistant.
        logger.warning(f"[spend_guard] check failed, allowing session: {exc}")


def today_summary() -> dict:
    """Current totals, for diagnostics and the monitor."""
    state = _read_state()
    state["usd_billed_est"] = _billed_estimate(state, _load_config())
    state["sessions_last_hour"] = _sessions_last_hour()
    return state
