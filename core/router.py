"""
core/router.py — model routing layer.

Maps agents to model providers based on data sensitivity.
Sensitive agents (diarist, pattern_miner, goals_interviewer) route to
local Ollama when local_enabled is true in config/modules/routing.yaml.
Falls back to cloud with a logged warning when local is disabled.

Every fallback is written to data/logs/routing_fallbacks.json so that
when Ollama comes online, you can see exactly which calls were leaking.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

_ROOT = Path(__file__).parent.parent
_ROUTING_CONFIG = _ROOT / "config" / "modules" / "routing.yaml"
_FALLBACK_LOG = _ROOT / "data" / "logs" / "routing_fallbacks.json"


@dataclass
class ModelConfig:
    provider: str           # "anthropic" | "openai" | "ollama" | "gemini"
    model: str | None       # override; None means use the provider's default
    base_url: str | None    # override; None means use the provider's default


def _load_routing() -> dict:
    if _ROUTING_CONFIG.exists():
        with open(_ROUTING_CONFIG) as f:
            return yaml.safe_load(f) or {}
    return {}


def resolve_model(agent: str) -> ModelConfig:
    """
    Resolve the provider and model to use for a given agent session.

    When the agent's target is 'local' but local_enabled is false, the
    configured fallback provider is used and the bypass is logged.

    Returns ModelConfig with provider, optional model override, and
    optional base_url override.
    """
    cfg = _load_routing()

    local_enabled: bool = cfg.get("local_enabled", False)
    local_cfg: dict = cfg.get("local", {})
    providers: dict = cfg.get("providers", {})
    agents: dict = cfg.get("agents", {})

    agent_cfg = agents.get(agent, {})
    target: str = agent_cfg.get("target", "cloud_deep")
    fallback: str = agent_cfg.get("fallback", "cloud_deep")

    if target == "local":
        if local_enabled:
            return ModelConfig(
                provider="ollama",
                model=local_cfg.get("model", "qwen3:14b"),
                base_url=local_cfg.get("endpoint", "http://localhost:11434/v1"),
            )
        # Local disabled — fall back to cloud and log it.
        _log_fallback(agent, target, fallback)
        target = fallback

    provider_cfg = providers.get(target, {})
    return ModelConfig(
        provider=provider_cfg.get("provider", "anthropic"),
        model=provider_cfg.get("model"),
        base_url=None,
    )


def _log_fallback(agent: str, intended: str, actual: str) -> None:
    """Record a local→cloud routing fallback for auditability."""
    _FALLBACK_LOG.parent.mkdir(parents=True, exist_ok=True)

    entries: list = []
    if _FALLBACK_LOG.exists():
        try:
            with open(_FALLBACK_LOG) as f:
                entries = json.load(f)
        except Exception:
            pass

    entries.append({
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "intended_target": intended,
        "actual_target": actual,
        "reason": "local_enabled: false",
    })

    with open(_FALLBACK_LOG, "w") as f:
        json.dump(entries, f, indent=2)
