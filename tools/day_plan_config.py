"""
tools/day_plan_config.py — the day planner's switches and weights, read from
config/modules/day_plan.yaml.

A module of its own because two layers read it: the task ledger (tools/obligations.py, which
hides its new schema parts behind `ledger_fields` and applies the unconfirmed rule behind
`unconfirmed_rule`) and the planner itself (tools/day_plan.py). Putting the loader in either
of those would make the other import it — a cycle, since the planner reads the ledger.

The file is re-read whenever its mtime changes, so a flag flip on the VM needs no restart.
Every read fails toward the shipped defaults below: a missing or broken file must not turn a
Stage B behaviour on, and it must not take a session down either.

Plan: archive/plans/day_planner_plan_2026-10-24.md § 10.
"""

from __future__ import annotations

import copy
import logging
import threading
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "config" / "modules" / "day_plan.yaml"

# What a missing or unreadable file means: Stage A as shipped, never more switched on.
_DEFAULTS: dict = {
    "flags": {
        "build": True, "show_in_app": True, "ledger_fields": False, "synth_reads_plan": False,
        "unconfirmed_rule": False, "reshuffle_model": False, "nudges": False,
        "owns_checkins": False,
    },
    "replaces_jobs": ["companion_checkin"],
    "score": {
        "priority": {"high": 30, "normal": 20, "low": 10},
        "goal": {"essential": 30, "linked": 20, "none": 15},
        "vital": {"overdue": 40, "due_today": 30, "due_tomorrow": 15, "in_lead": 5},
        "missable": {"due_today": 10, "lapsed": 0},
        "habit": {"planned_day": 10, "at_risk": 15, "daily": 10},
        "interval_due": 15,
        "medication": 50,
        "reshuffle_delta": 10,
    },
    "limits": {
        "reshuffle_gap_minutes": 15, "reshuffles_per_day": 12, "travel_lookups_per_day": 60,
        "travel_assumed_minutes": 30, "snapshot_max_age_minutes": 10,
        "calendar_fetch_timeout_seconds": 3, "frozen_minutes": 20, "default_task_minutes": 30,
        "reshuffle_stale_seconds": 180, "reply_lock_ms": 200, "length_asks_per_day": 2, "log_retention_days": 90,
        "plan_retention_days": 3,
    },
}

_LOCK = threading.Lock()
_CACHE: dict = {"mtime": None, "cfg": None}

# Tests point this at a temp file, or set an override dict directly.
_OVERRIDE: dict | None = None


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path: Path | None = None) -> dict:
    """The merged config: shipped defaults overlaid with the file. Never raises."""
    if _OVERRIDE is not None:
        return _merge(_DEFAULTS, _OVERRIDE)
    p = path or _PATH
    try:
        mtime = p.stat().st_mtime_ns
    except OSError:
        return copy.deepcopy(_DEFAULTS)
    with _LOCK:
        if _CACHE["mtime"] == mtime and _CACHE["cfg"] is not None and path is None:
            return copy.deepcopy(_CACHE["cfg"])
        try:
            raw = yaml.safe_load(p.read_text()) or {}
            if not isinstance(raw, dict):
                raise ValueError("top level is not a mapping")
            cfg = _merge(_DEFAULTS, raw)
        except Exception as exc:  # noqa: BLE001 — a broken file means the defaults, not a crash
            logger.warning(f"[day_plan] config unreadable, using defaults: {exc}")
            cfg = copy.deepcopy(_DEFAULTS)
        if path is None:
            _CACHE.update(mtime=mtime, cfg=cfg)
        return copy.deepcopy(cfg)


def flag(name: str) -> bool:
    """One switch. Unknown names are off."""
    return bool((load().get("flags") or {}).get(name, False))


def limit(name: str):
    return (load().get("limits") or {}).get(name, _DEFAULTS["limits"].get(name))


def score_weights() -> dict:
    return load().get("score") or copy.deepcopy(_DEFAULTS["score"])
